# version 0.9.0 221115 09:10:26

* replaced `requirements.txt` with `pipenv`
* removed relative imports
* BoundingBox comparison now acknowledges state attributes _scale, _transform_x, and transform_y
* `map_ids_to_bounding_boxes` now accepts multiple element args
* `map_ids_to_bounding_boxes` now returns a bounding box for root elements
* `map_ids_to_bounding_boxes` now adds a random id to each element without an id
* deprecated helper functions `deepcopy_element` and `get_bounding_box`
* replaced BoundingBox method `merge` with classmethod `merged`

