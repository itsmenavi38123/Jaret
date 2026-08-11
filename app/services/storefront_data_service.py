import re
from typing import Dict, Any, List, Optional
from app.services.google_places_service import google_places_service
from app.services.facebook_token_service import facebook_token_service
from app.services.facebook_service import facebook_service
from app.services.firecrawl_service import firecrawl_service

# Per-job image cap (acceptance criteria B7): bounds the Fable vision spend per
# location per run regardless of how many sources contribute photos.
MAX_IMAGES_PER_LOCATION = 6


class StorefrontDataService:
    async def collect_storefront_data(
        self,
        user_id: str,
        business_name: str,
        address: str,
        lat: float,
        lng: float,
        website_url: Optional[str] = None,
        density_tier: str = "urban"
    ) -> Dict[str, Any]:
        """
        Ingest storefront photos and surrounding POI counts from all configured sources:
        1. Google Places (Public business photos + Nearby Search context)
        2. Google Street View (Street view static photo)
        3. Facebook Graph API (Business page photos using saved user Page Access Tokens)
        4. Firecrawl website scraper (Scrapes user website to extract storefront/interior images)
        """
        
        # 1. Google Places & Surrounding Area counts
        google_place = await google_places_service.find_business(
            business_name=business_name,
            address=address
        )
        
        google_photos = []
        place_id = None
        business_status = "OPERATIONAL"
        if google_place:
            place_id = google_place.get("id")
            business_status = google_place.get("businessStatus", "OPERATIONAL")
            photo_objs = google_place.get("photos", [])[:3]  # Limit to top 3 photos
            for photo in photo_objs:
                name = photo.get("name")
                if name:
                    base64_photo = await google_places_service.get_photo_base64(name)
                    if base64_photo:
                        google_photos.append({
                            "source": "google_places",
                            "name": name,
                            "base64": base64_photo
                        })

        # Calculate density-based radius (dense-urban = 150m, suburban = 500m, rural = 1600m)
        radius = 150.0
        if density_tier == "suburban":
            radius = 500.0
        elif density_tier == "rural":
            radius = 1600.0

        nearby = await google_places_service.search_nearby(lat, lng, radius)
        poi_count = len(nearby)
        closed_count = sum(1 for p in nearby if p.get("businessStatus") == "CLOSED_PERMANENTLY")
        active_count = poi_count - closed_count

        # 2. Google Street View Image
        street_view_result = await google_places_service.get_street_view_image_base64(lat, lng)

        # 3. Facebook Graph API Photos
        facebook_photos = []
        tokens = await facebook_token_service.get_tokens_by_user(user_id)
        active_tokens = [t for t in tokens if t.is_active]
        if active_tokens:
            primary_token = active_tokens[0]
            fb_photo_objs = await facebook_service.get_page_photos(
                page_id=primary_token.page_id,
                page_access_token=primary_token.access_token,
                limit=3
            )
            for photo in fb_photo_objs:
                images = photo.get("images", [])
                if images:
                    # images[0] is the largest resolution
                    largest_img_url = images[0].get("source")
                    if largest_img_url:
                        base64_img = await facebook_service.download_image_as_base64(largest_img_url)
                        if base64_img:
                            facebook_photos.append({
                                "source": "facebook",
                                "id": photo.get("id"),
                                "base64": base64_img
                            })

        # 4. Firecrawl Website Scraping
        website_photos = []
        if website_url:
            try:
                scrape_res = await firecrawl_service.scrape(website_url)
                if scrape_res.get("success") and scrape_res.get("markdown"):
                    markdown_content = scrape_res["markdown"]
                    # Extract image URLs from markdown format: ![alt](url)
                    img_urls = re.findall(r"!\[.*?\]\((.*?)\)", markdown_content)
                    
                    # Filter for likely storefront/interior images, or fall back to first few
                    valid_urls = []
                    for url in img_urls:
                        # Clean up URL (remove spaces, markdown extensions)
                        clean_url = url.split(" ")[0].strip()
                        if clean_url.startswith("http"):
                            valid_urls.append(clean_url)
                            
                    # Download up to 3 website images
                    for url in valid_urls[:3]:
                        base64_img = await facebook_service.download_image_as_base64(url)
                        if base64_img:
                            website_photos.append({
                                "source": "website",
                                "url": url,
                                "base64": base64_img
                            })
            except Exception as ex:
                print(f"Failed to scrape website via Firecrawl: {ex}")

        # Assemble unified payload
        all_images = []
        if street_view_result:
            all_images.append({
                "source": "street_view",
                "base64": street_view_result["base64"],
                "capture_date": street_view_result.get("capture_date"),
            })
        all_images.extend(google_photos)
        all_images.extend(facebook_photos)
        all_images.extend(website_photos)

        # Enforce the combined per-location image cap; log what's dropped rather
        # than silently truncating (no silent caps).
        if len(all_images) > MAX_IMAGES_PER_LOCATION:
            print(
                f"[Storefront] Image cap reached for {business_name}: "
                f"{len(all_images)} collected, capping to {MAX_IMAGES_PER_LOCATION} "
                f"(dropped {len(all_images) - MAX_IMAGES_PER_LOCATION})"
            )
            all_images = all_images[:MAX_IMAGES_PER_LOCATION]

        return {
            "location_id": place_id,
            "business_status": business_status,
            "images": all_images,
            "geographic_vitality": {
                "density_tier": density_tier,
                "radius_meters": radius,
                "total_nearby_poi": poi_count,
                "active_poi": active_count,
                "permanently_closed_poi": closed_count,
                "open_closed_ratio": active_count / max(closed_count, 1)
            }
        }

storefront_data_service = StorefrontDataService()
