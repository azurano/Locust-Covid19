# -*- coding: utf-8 -*-
"""
The aim of this module is to extract the cropland area per district.

Created on Mon Jul 13 11:16:40 2020

@author: ioanna.papachristou@accenture.com
"""

# Imports
import pandas as pd
import geopandas as gpd
from utils_flat_files import FlatFiles
from rasterstats import zonal_stats

#S3 paths
# INPUT_PATH = r's3://mercy-locust-covid19-in-dev/inbound/sourcedata/Spatial/'
# OUTPUT_PATH = r's3://mercy-locust-covid19-out-dev/location_dim/'

#local paths
INPUT_PATH = r'data/input/'
OUTPUT_PATH = r'data/output/'

#RASTER_NAMES = ["N00E30", "S10E40", "S10E30", "S10E20", "N10E50", "N10E40", "N10E30", "N00E50", "N00E40", "N00E20"] #if project extended to more countries, their corresponding geotiffs refering to croplands could be added here in the list
RASTER_NAMES = ["N00E30", "S10E40", "N00E50"]

class Cropland:
    '''
    This class calculates the cropland area per district.
    '''
    def __init__(self, path_in = INPUT_PATH, path_out = OUTPUT_PATH):
        self.path_in = path_in
        self.path_out = path_out

        # Import districts
        self.shp2_Kenya = gpd.read_file(self.path_in + "gadm36_KEN_2.shp")[['GID_2', 'geometry']]
        self.shp2_Somalia = gpd.read_file(self.path_in + "gadm36_SOM_2.shp")[['GID_2', 'geometry']]
        self.shp2_Ethiopia = gpd.read_file(self.path_in + "gadm36_ETH_2.shp")[['GID_2', 'geometry']]
        self.shp2_Uganda = gpd.read_file(self.path_in + "gadm36_UGA_2.shp")[['GID_2', 'geometry']]

        # Import cropland vector
        #self.crops = gpd.read_file(self.path_in + "crops/Crops_vectorized.shp")


    def get_districts(self):
        '''
        
        :return: A geodataframe with all districts of the 4 countries concatenated.
        '''
        district_level = [self.shp2_Kenya, self.shp2_Ethiopia, self.shp2_Somalia, self.shp2_Uganda]
        gdf_districts = gpd.GeoDataFrame(pd.concat(district_level, ignore_index=True))
        gdf_districts['area'] = gdf_districts.geometry.area
        gdf_districts.crs = {"init": "epsg:4326"}
        return gdf_districts

    def get_stats(self):
        gdf = gpd.GeoDataFrame()

        for raster in RASTER_NAMES:
            raster_path = self.path_in + "cropland/GFSAD30AFCE_2015_" + raster + "_001_2017261090100.tif"
            gdf_districts = self.get_districts()

            stats = zonal_stats(gdf_districts.geometry, raster_path, stats="count", categorical=True)

            if raster == "N00E50":
                gdf_districts['croplands_count'] = pd.DataFrame.from_dict(stats)[1]
            else:
                gdf_districts['croplands_count'] = pd.DataFrame.from_dict(stats)[2]
            print(raster)
            gdf_districts['area_count'] = pd.DataFrame.from_dict(stats)["count"]
            gdf_districts = gdf_districts[gdf_districts['croplands_count'].notnull()]
            gdf_districts['croplands_area'] = gdf_districts['croplands_count'] * gdf_districts['area'] / gdf_districts['area_count']
            print(gdf_districts.shape)
            gdf = gdf.append(gdf_districts)
            print(gdf.head())
        return gdf

    # def filter_crops(self):
    #     '''
    #
    #     :return: The crops vector filtered by the crops id.
    #     '''
    #
    #     crops = self.crops
    #     crops = crops[crops['Crops'] == 1]
    #     crops.Crops = 12
    #     return crops

    # def crops_district(self):
    #     '''
    #
    #     :return: A geodataframe with the crops intersected by district.
    #     '''
    #     crops = gpd.GeoDataFrame(self.filter_crops())
    #     gdf_districts = self.get_districts()
    #     crops_district = gpd.overlay(crops, gdf_districts, how='intersection')
    #     return crops_district
    #
    # def crops_area(self):
    #     '''
    #
    #     :return: A geodataframe with the area of crops per district calculated.
    #     '''
    #     crops_district = gpd.GeoDataFrame(self.crops_district())
    #     crops_district['area_inter'] = crops_district.geometry.area
    #     return crops_district

    def add_fact_ids(self):
        '''
        Adds the fact tables ids
        :return:  A filtered dataframe by the columns we need for fact tables.
        '''
        crops_district = (self.get_stats())
        crops_district['measureID'] = 27
        crops_district['factID'] = 'CROP_' + crops_district.index
        crops_district['year'] = 2015
        #crops_district['date'] = pd.to_datetime([f'{y}-01-01' for y in crops_district.year])
        crops_district['locationID'] = crops_district['GID_2']
        crops_district['value'] = crops_district['croplands_area']

        # Add dateID
        crops_gdf = FlatFiles().add_date_id(crops_district, column = 'year')

        # Select fact table columns
        crops_df = FlatFiles().select_columns_fact_table(df = crops_gdf)
        
        return crops_df

    def export_table(self, filename):
        '''

        :return: The Cropland table in both a parquet and csv format with the date added in the name.
        '''
        crops_df = self.add_fact_ids()
        FlatFiles().export_output_w_date(crops_df, filename)
        
if __name__ == '__main__':

    print("------- Extracting cropland area per district table ---------")

    gdf = Cropland().get_stats()
    print(gdf.shape)
    print(gdf.columns)

    Cropland().export_table("Cropland")