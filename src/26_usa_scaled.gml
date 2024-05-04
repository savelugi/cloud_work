graph [
  name "usanet_26_latlon"
  node [
    id 0
    label "0"
    Latitude 35.22
    Longitude -80.83
    City "Charlotte"
    server [
      type "core"
      cpu 32
      memory 128
      gpu 0
    ]
  ]
  node [
    id 1
    label "1"
    Latitude 33.74
    Longitude -84.41
    City "Atlanta"
    server [
      type "core"
      cpu 64
      memory 64
      gpu 1
    ]
  ]
  node [
    id 2
    label "2"
    Latitude 39.77
    Longitude -86.16
    City "Indianapolis"
    server [
      type "edge"
      cpu 32
      memory 8
      gpu 0
    ]
  ]
  node [
    id 3
    label "3"
    Latitude 35.46
    Longitude -97.52
    City "Oklahoma City"
    server [
      type "edge"
      cpu 16
      memory 64
      gpu 0
    ]
  ]
  node [
    id 4
    label "4"
    Latitude 39.74
    Longitude -104.99
    City "Denver"
    server [
      type "core"
      cpu 128
      memory 32
      gpu 0
    ]
  ]
  node [
    id 5
    label "5"
    Latitude 39.09
    Longitude -94.58
    City "Kansas City"
    server [
      type "edge"
      cpu 8
      memory 64
      gpu 0
    ]
  ]
  node [
    id 6
    label "6"
    Latitude 40.71
    Longitude -111.9
    City "Salt Lake City"
    server [
      type "edge"
      cpu 8
      memory 32
      gpu 0
    ]
  ]
  node [
    id 7
    label "7"
    Latitude 35.16
    Longitude -115.15
    City "Las Vegas"
    server [
      type "core"
      cpu 64
      memory 256
      gpu 1
    ]
  ]
  node [
    id 8
    label "8"
    Latitude 47.57
    Longitude -122.32
    City "Seattle"
    server [
      type "edge"
      cpu 16
      memory 32
      gpu 0
    ]
  ]
  node [
    id 9
    label "9"
    Latitude 37.78
    Longitude -122.41
    City "San Francisco"
    server [
      type "core"
      cpu 48
      memory 64
      gpu 1
    ]
  ]
  node [
    id 10
    label "10"
    Latitude 33.84
    Longitude -118.24
    City "Los Angeles"
    server [
      type "edge"
      cpu 8
      memory 64
      gpu 0
    ]
  ]
  node [
    id 11
    label "11"
    Latitude 32.78
    Longitude -96.79
    City "Dallas"
    server [
      type "core"
      cpu 128
      memory 256
      gpu 1
    ]
  ]
  node [
    id 12
    label "12"
    Latitude 29.74
    Longitude -95.35
    City "Houston"
    server [
      type "core"
      cpu 128
      memory 128
      gpu 0
    ]
  ]
  node [
    id 13
    label "13"
    Latitude 30.0
    Longitude -90.11
    City "New Orleans"
    server [
      type "core"
      cpu 48
      memory 64
      gpu 1
    ]
  ]
  node [
    id 14
    label "14"
    Latitude 25.78
    Longitude -80.22
    City "Miami"
    server [
      type "core"
      cpu 128
      memory 128
      gpu 1
    ]
  ]
  node [
    id 15
    label "15"
    Latitude 38.9
    Longitude -77.03
    City "Washington D.C."
    server [
      type "core"
      cpu 64
      memory 32
      gpu 0
    ]
  ]
  node [
    id 16
    label "16"
    Latitude 40.73
    Longitude -73.99
    City "New York"
    server [
      type "core"
      cpu 48
      memory 64
      gpu 0
    ]
  ]
  node [
    id 17
    label "17"
    Latitude 42.36
    Longitude -71.06
    City "Boston"
    server [
      type "core"
      cpu 32
      memory 256
      gpu 0
    ]
  ]
  node [
    id 18
    label "18"
    Latitude 43.71
    Longitude -79.4
    City "Toronto"
    server [
      type "edge"
      cpu 16
      memory 16
      gpu 0
    ]
  ]
  node [
    id 19
    label "19"
    Latitude 41.5
    Longitude -81.69
    City "Cleveland"
    server [
      type "edge"
      cpu 8
      memory 16
      gpu 0
    ]
  ]
  node [
    id 20
    label "20"
    Latitude 42.34
    Longitude -83.13
    City "Detroit"
    server [
      type "core"
      cpu 32
      memory 64
      gpu 1
    ]
  ]
  node [
    id 21
    label "21"
    Latitude 41.86
    Longitude -87.67
    City "Chicago"
    server [
      type "edge"
      cpu 16
      memory 32
      gpu 0
    ]
  ]
  node [
    id 22
    label "22"
    Latitude 31.79
    Longitude -106.39
    City "El Paso"
    server [
      type "edge"
      cpu 8
      memory 64
      gpu 0
    ]
  ]
  node [
    id 23
    label "23"
    Latitude 44.98
    Longitude -93.25
    City "Minneapolis"
    server [
      type "edge"
      cpu 16
      memory 32
      gpu 0
    ]
  ]
  node [
    id 24
    label "24"
    Latitude 36.16
    Longitude -86.77
    City "Nashville"
    server [
      type "core"
      cpu 64
      memory 256
      gpu 1
    ]
  ]
  node [
    id 25
    label "25"
    Latitude 38.63
    Longitude -90.19
    City "Saint Louis"
    server [
      type "core"
      cpu 32
      memory 256
      gpu 1
    ]
  ]
  edge [
    source 0
    target 24
    length 6.013917192645736
    link_bandwith "25G"
  ]
  edge [
    source 0
    target 15
    length 5.289839317030337
    link_bandwith "25G"
  ]
  edge [
    source 0
    target 1
    length 3.873861122962461
    link_bandwith "25G"
  ]
  edge [
    source 1
    target 14
    length 8.99542661578649
    link_bandwith "25G"
  ]
  edge [
    source 1
    target 13
    length 6.817448202956884
    link_bandwith "25G"
  ]
  edge [
    source 1
    target 24
    length 3.38023667810406
    link_bandwith "25G"
  ]
  edge [
    source 2
    target 24
    length 3.6611746748823726
    link_bandwith "10G"
  ]
  edge [
    source 2
    target 25
    length 4.188138011097535
    link_bandwith "10G"
  ]
  edge [
    source 2
    target 21
    length 2.578410362994999
    link_bandwith "1G"
  ]
  edge [
    source 2
    target 19
    length 4.7930992061504405
    link_bandwith "1G"
  ]
  edge [
    source 3
    target 25
    length 7.986100425113623
    link_bandwith "10G"
  ]
  edge [
    source 3
    target 5
    length 4.671241804916548
    link_bandwith "1G"
  ]
  edge [
    source 3
    target 11
    length 2.7776428856136244
    link_bandwith "10G"
  ]
  edge [
    source 4
    target 6
    length 6.977750353803161
    link_bandwith "10G"
  ]
  edge [
    source 4
    target 5
    length 10.430273246660411
    link_bandwith "10G"
  ]
  edge [
    source 4
    target 11
    length 10.755538108342131
    link_bandwith "25G"
  ]
  edge [
    source 5
    target 25
    length 4.414034435751494
    link_bandwith "10G"
  ]
  edge [
    source 5
    target 23
    length 6.038294461186861
    link_bandwith "1G"
  ]
  edge [
    source 6
    target 8
    length 12.475415824733048
    link_bandwith "1G"
  ]
  edge [
    source 6
    target 9
    length 10.910774491299865
    link_bandwith "10G"
  ]
  edge [
    source 6
    target 7
    length 6.431562796086193
    link_bandwith "10G"
  ]
  edge [
    source 7
    target 10
    length 3.3601339259023466
    link_bandwith "10G"
  ]
  edge [
    source 7
    target 22
    length 9.385867035069273
    link_bandwith "10G"
  ]
  edge [
    source 8
    target 9
    length 9.790413678696114
    link_bandwith "10G"
  ]
  edge [
    source 9
    target 10
    length 5.736941693969008
    link_bandwith "10G"
  ]
  edge [
    source 10
    target 22
    length 12.026013470805688
    link_bandwith "1G"
  ]
  edge [
    source 11
    target 22
    length 9.650911874014803
    link_bandwith "10G"
  ]
  edge [
    source 11
    target 24
    length 10.574724582701915
    link_bandwith "25G"
  ]
  edge [
    source 11
    target 12
    length 3.3638073666605894
    link_bandwith "25G"
  ]
  edge [
    source 12
    target 22
    length 11.228717647175928
    link_bandwith "10G"
  ]
  edge [
    source 12
    target 13
    length 5.24644641638509
    link_bandwith "25G"
  ]
  edge [
    source 13
    target 14
    length 10.7526973360176
    link_bandwith "25G"
  ]
  edge [
    source 15
    target 16
    length 3.548309456628611
    link_bandwith "25G"
  ]
  edge [
    source 15
    target 19
    length 5.3362533672980685
    link_bandwith "10G"
  ]
  edge [
    source 16
    target 17
    length 3.3528793595952666
    link_bandwith "25G"
  ]
  edge [
    source 16
    target 19
    length 7.7384042282630885
    link_bandwith "10G"
  ]
  edge [
    source 16
    target 18
    length 6.176447198835277
    link_bandwith "10G"
  ]
  edge [
    source 17
    target 18
    length 8.448556089652246
    link_bandwith "10G"
  ]
  edge [
    source 18
    target 20
    length 3.9736381314860463
    link_bandwith "10G"
  ]
  edge [
    source 19
    target 20
    length 1.6670932787339763
    link_bandwith "10G"
  ]
  edge [
    source 20
    target 21
    length 4.565303932927145
    link_bandwith "10G"
  ]
  edge [
    source 21
    target 25
    length 4.096742608463456
    link_bandwith "10G"
  ]
  edge [
    source 21
    target 23
    length 6.393027451841574
    link_bandwith "1G"
  ]
]
