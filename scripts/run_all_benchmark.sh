#!/usr/bin/env bash

. run_benchmark.sh 01_module_list.sh
sleep 5
. run_benchmark.sh 02_dataset_list.sh
sleep 5
. run_benchmark.sh 03_view_list.sh
sleep 5
. run_benchmark.sh 04_view_detail.sh
sleep 5
. run_benchmark.sh 05_view_for_user.sh
sleep 5
. run_benchmark.sh 06_entity_list_0.sh
sleep 5
. run_benchmark.sh 07_entity_list_1.sh
sleep 5
. run_benchmark.sh 08_entity_list_2.sh
sleep 5
. run_benchmark.sh 09_entity_list_1_concept_ucode.sh
sleep 5
. run_benchmark.sh 10_entity_list_1_ucode.sh
sleep 5
. run_benchmark.sh 11_entity_list_by_type.sh
sleep 5
. run_benchmark.sh 12_entity_list_by_type_ucode.sh
sleep 5
. run_benchmark.sh 13_entity_list_version_concept_ucode.sh
sleep 5
. run_benchmark.sh 14_entity_list_version_ucode.sh
sleep 5
. run_benchmark.sh 15_entity_list.sh
sleep 5
. run_benchmark.sh 16_search_entity_by_name.sh
sleep 5
. run_benchmark.sh 17_search_children_by_ucode.sh
sleep 5
. run_benchmark.sh 18_search_parent_by_ucode.sh
sleep 5
. run_benchmark.sh 19_find_bbox_entity.sh
sleep 5
# containment check results error: SSL unexpected eof while reading ...
# . run_benchmark.sh 20_containment_check_0.sh
# sleep 5
# . run_benchmark.sh 21_containment_check_1.sh
# sleep 5
. run_benchmark.sh 22_entity_list_1_with_centroid.sh
sleep 5
. run_benchmark.sh 23_vector_tile.sh
sleep 5