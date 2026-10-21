// ЛР6: работа с MongoDB через Mongo Shell (часть 2 методички).
// Запуск: docker compose exec mongo mongo /lab/shell_demo.js
db = db.getSiblingDB('SeriesDB');   // = use SeriesDB
db.series.drop();                   // чтобы демо можно было запускать повторно

function show(title, value) {
  print('\n> ' + title);
  printjson(value);
}

show('db.series.insertOne({ name: "The Blacklist", year: 2013 })',
     db.series.insertOne({ name: 'The Blacklist', year: 2013 }));

show('db.series.insertMany([...])', db.series.insertMany([
  { name: 'Game of Thrones', year: 2012 },
  { name: 'House of Cards', year: 2013 },
  { name: 'Suits', year: 2011 },
]));

show('db.series.find({})  -- SELECT * FROM series', db.series.find({}).toArray());

show('db.series.find({ year: 2013 })  -- SELECT * FROM series WHERE year = 2013',
     db.series.find({ year: 2013 }).toArray());

show('db.series.updateOne({ name: "Suits" }, { $set: { year: 2010 } })',
     db.series.updateOne({ name: 'Suits' }, { $set: { year: 2010 } }));
show('db.series.find({ name: "Suits" })', db.series.find({ name: 'Suits' }).toArray());

show('db.series.deleteMany({ year: 2012 })', db.series.deleteMany({ year: 2012 }));

show('db.series.find({})  -- после удаления', db.series.find({}).toArray());
