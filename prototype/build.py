import json,re
d={"report":json.load(open('../mock/report.json')),"scenes":json.load(open('../mock/scenes.json'))["scenes"],"meta":json.load(open('../mock/meta.json'))}
h=open('template.html').read().replace('__DATA__',json.dumps(d,ensure_ascii=False),1)
open('index.html','w').write(h);print('built',len(h))
