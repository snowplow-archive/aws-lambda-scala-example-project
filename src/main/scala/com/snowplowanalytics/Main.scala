/*
 * Copyright (c) 2015 Snowplow Analytics Ltd. All rights reserved.
 *
 * This program is licensed to you under the Apache License Version 2.0,
 * and you may not use this file except in compliance with the Apache License Version 2.0.
 * You may obtain a copy of the Apache License Version 2.0 at http://www.apache.org/licenses/LICENSE-2.0.
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the Apache License Version 2.0 is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the Apache License Version 2.0 for the specific language governing permissions and limitations there under.
 */
package com.snowplowanalytics

import com.amazonaws.services.lambda.runtime.events.KinesisEvent
import scala.collection.JavaConversions._
import scala.collection.mutable.Buffer
import awscala._, dynamodbv2._


class ProcessKinesisEvents {
	    
    import com.fasterxml.jackson.databind.ObjectMapper
    import com.fasterxml.jackson.module.scala.DefaultScalaModule
    

    val scalaMapper = {  
        new ObjectMapper().registerModule(new DefaultScalaModule)
    }

    def recordHandler(event: KinesisEvent) {

        val convertedRecords =
            for {
                rec <- event.getRecords 
                val record = new String(rec.getKinesis.getData.array())
                val event = scalaMapper.readValue(record, classOf[SimpleEvent])
            } yield event
        
        def aggregateRecords(converted: Buffer[SimpleEvent]) {
            val eventArray = converted.groupBy(_.bucket).mapValues(_.map(x => x.eventType))
            val counted = eventArray.mapValues(_.groupBy(identity).mapValues(_.size))

            // sets DynamoDB client to us-east-1
            implicit val dynamoDB = DynamoDB.at(Region.US_EAST_1)

            // sets dynamodb table name
            val tableName = "my-table"
            
            // sets up table and dynamodb connection
            val table: Table = dynamoDB.table(tableName).get

            // atomic increments with addAttributes
            for (bucket <- counted)
                bucket._2.map( { 
                    case (key, value) =>
                    table.addAttributes(bucket._1, key, Seq("Count" -> value))
            })
        }
        aggregateRecords(convertedRecords)
	}
}

