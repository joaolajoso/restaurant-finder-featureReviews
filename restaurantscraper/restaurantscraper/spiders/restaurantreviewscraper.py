# -*- coding: utf-8 -*-
import scrapy
import time
from scrapy.selector import Selector
from selenium import webdriver
from restaurantscraper.items import RestaurantscraperItem

MAX_RESTAURANTS = 10	# collect information from each
MAX_REVIEWS = 20		# collect reviews from each restaurants

class RestaurantreviewscraperSpider(scrapy.Spider):
	name = 'restaurantreviewscraper'
	allowed_domains = ['tripadvisor.com']
	start_urls = [
		'https://www.tripadvisor.com/Restaurants-g186338-London_England.html'
	]	
	
	def __init__(self):
		self.restaurants_scraped = 0
		
	def parse(self, response):
		# yield restaurant information
		for restaurant in response.css('a.property_title'):
			self.restaurants_scraped += 1
			if (self.restaurants_scraped > MAX_RESTAURANTS):
				return
			res_url = ('https://www.tripadvisor.com%s' % \
				restaurant.xpath('@href').extract_first())
			yield scrapy.Request(res_url, callback=self.parse_restaurant)

		# move to the next page of restaurants
		next_page = ('https://www.tripadvisor.com%s'\
			% (response.css('a.nav.next.rndBtn.ui_button.primary.taLnk')) \
										.xpath('@href').extract_first())
		print('NEXT PAGE: ' + next_page)
		if next_page:
			yield scrapy.Request(next_page, callback=self.parse)
		
	def parse_restaurant(self, response):
		hasReviews = True
		sel = Selector(response)

		# start the webdriver to crawl reviews
		driver = webdriver.Chrome()

		# initialize Item class to access the fields
		rest_item = RestaurantscraperItem()

		# extract restaurant name
		rest_item['rest_name'] = sel.xpath('//h1/text()').extract()[1]

		# extract restaurant addr 
		street = response.xpath('//*[@id="taplc_restaurants_detail_info_content_0"]/div[4]/div[2]/span[2]/text()').extract_first()
		rest_item['rest_addr'] = street + ", London, UK" 

		# extract location
		if (response.xpath('//*[@id="LOCATION_TAB"]/div[2]/div[1]/div/div[1]/text()')):
			rest_item['rest_location'] = response.xpath('//*[@id="LOCATION_TAB"]/div[2]/div[1]/div/div[1]/text()').extract_first().replace('\n',"")
		else:
			rest_item['rest_location'] = "Unknown"

		# extract cuisine info
		rest_item['rest_cuisines'] = \
			response.xpath('//*[@id="taplc_restaurants_detail_info_content_0"]/div[2]/div/div[2]/div[2]/text()').extract_first()

		# extract restaurant rank
		if (response.css('div.prw_rup.prw_restaurants_header_eatery_pop_index')):
			rest_item['rest_rank'] = sel.xpath('//b/span/text()').extract()[0]
		else:
			rest_item['rest_rank'] = None

		# extract ratings
		if (response.css('span.overallRating')):
			rest_item['rest_rating'] = float(response.css('span.overallRating::text').extract_first())
		else:
			rest_item['rest_rating'] = 0

		# extract price
		rest_item['rest_price'] = \
			response.xpath('//*[@id="taplc_restaurants_detail_info_content_0"]/div[2]/span/span/text()').extract_first()

		# extract restaurant features	

		row_four_features = \
		(response.xpath('//*[@id="RESTAURANT_DETAILS"]/div[2]/div[1]/div[4]/div[1]/text()').extract_first().replace("\n", ""))
		row_five_features = \
		(response.xpath('//*[@id="RESTAURANT_DETAILS"]/div[2]/div[1]/div[5]/div[1]/text()').extract_first().replace("\n", ""))
		
		if (row_four_features == "Restaurant features"):
			rest_item['rest_features'] = \
			response.xpath('//*[@id="RESTAURANT_DETAILS"]/div[2]/div[1]/div[4]/div[2]/text()').extract_first()
		elif (row_five_features == "Restaurant features"):
			rest_item['rest_features'] = \
			response.xpath('//*[@id="RESTAURANT_DETAILS"]/div[2]/div[1]/div[5]/div[2]/text()').extract_first()
		else:
			rest_item['rest_features'] = None 

		# extract restaurant meals
		
		row_three_meals = \
		(response.xpath('//*[@id="RESTAURANT_DETAILS"]/div[2]/div[1]/div[3]/div[1]/text()').extract_first().replace("\n", ""))
		row_four_meals = \
		(response.xpath('//*[@id="RESTAURANT_DETAILS"]/div[2]/div[1]/div[4]/div[1]/text()').extract_first().replace("\n", ""))

		if (row_three_meals == "Meals"):
			rest_item['rest_meals'] = \
			response.xpath('//*[@id="RESTAURANT_DETAILS"]/div[2]/div[1]/div[3]/div[2]/text()').extract_first()
		elif (row_four_meals == "Meals"):
			rest_item['rest_meals'] = \
			response.xpath('//*[@id="RESTAURANT_DETAILS"]/div[2]/div[1]/div[4]/div[2]/text()').extract_first()
		else:
			rest_item['rest_meals'] = None

		# extract positive and negative reviews count
		excellent_count = int(response.xpath('//*[@id="ratingFilter"]/ul/li[1]/label/span[2]/text()').extract_first())
		good_count = int(response.xpath('//*[@id="ratingFilter"]/ul/li[2]/label/span[2]/text()').extract_first())
		rest_item['rest_pos_count'] = excellent_count + good_count

		avg_count = int(response.xpath('//*[@id="ratingFilter"]/ul/li[3]/label/span[2]/text()').extract_first())
		poor_count = int(response.xpath('//*[@id="ratingFilter"]/ul/li[4]/label/span[2]/text()').extract_first())
		terrible_count = int(response.xpath('//*[@id="ratingFilter"]/ul/li[5]/label/span[2]/text()').extract_first())
		rest_item['rest_neg_count'] = avg_count + poor_count + terrible_count

		# extract total number of reviews 
		if (response.css('a.seeAllReviews')):
			rest_item['rest_total_reviews'] = \
			int(response.xpath('//*[@id="taplc_location_review_filter_controls_0_form"]/div[4]/ul/li[2]/label/span/text()') \
								.extract_first().strip('()').replace(",", ""))
		else:
			hasReviews = False
			rest_item['rest_total_reviews'] = 0

		# extract reviews 
		if hasReviews:
			reviews = []
			url = response.url
			try:
				driver.get(url)
			except:
				pass
			time.sleep(4)
			while len(reviews) < MAX_REVIEWS:
				reviews += self.parse_reviews(driver)
				print('Fetched a total of {} reviews by now.'.format(len(reviews)))
				next_button = driver.find_element_by_class_name('next')
				if 'disabled' in next_button.get_attribute('class'):
					break
				next_button.click()
				time.sleep(5)
			rest_item['rest_reviews'] = reviews
			driver.close()
		yield rest_item

	def parse_reviews(self,driver):
		reviews = []
		try:
			driver.find_element_by_class_name('ulBlueLinks').click()
		except:
			pass
		time.sleep(5)
		review_containers = driver.find_elements_by_class_name('reviewSelector')
		for review in review_containers:
			review_text = review.find_element_by_class_name('partial_entry').text.replace('\n', '')
			reviews.append(review_text)
		return reviews
