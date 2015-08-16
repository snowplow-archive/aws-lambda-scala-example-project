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
package com.snowplowanalytics.awslambda

// Java
import java.util.Date
import java.util.TimeZone
import java.text.SimpleDateFormat

// AWS
import com.amazonaws.auth.profile.ProfileCredentialsProvider
import com.amazonaws.services.dynamodbv2.AmazonDynamoDBClient
import com.amazonaws.services.dynamodbv2.document.{AttributeUpdate, DynamoDB, Item}

/**
 * Object sets up singleton that finds AWS credentials for DynamoDB to access the
 * aggregation records table. The utility function below puts items into the
 * "AggregateRecords" table.
 *
 * val dynamoConnection = DynamoUtils.setupDynamoClientConnection(config.awsProfile)
 */
object DynamoDBUtility {

  val dateFormatter = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
  val timezone = TimeZone.getTimeZone("UTC")

  /**
   * Function timezone helper
   */
  def timeNow(): String = {
    dateFormatter.setTimeZone(timezone)
    dateFormatter.format(new Date())
  }

  /**
   * Function wraps DynamoDB cred setup
   * Lambda creds pass IAM to DB Client
   */
  def setupDynamoClientConnection(): DynamoDB = {
    val dynamoDB = new DynamoDB(new AmazonDynamoDBClient())
    dynamoDB
  }

  /**
   * Function wraps AWS Java putItem operation to DynamoDB table
   */
  def putItem(dynamoDB: DynamoDB, tableName: String, bucketStart: String, eventType: String, createdAt: String,  updatedAt: String, count: Int) {

    // AggregateRecords column names
    val tablePrimaryKeyName = "BucketStart"
    val tableEventTypeSecondaryKeyName = "EventType"
    val tableCreatedAtColumnName = "CreatedAt"
    val tableUpdatedAtColumnName = "UpdatedAt"
    val tableCountColumnName = "Count"

    try {
      val time = new Date().getTime - (1 * 24 * 60 * 60 * 1000)
      val date = new Date()
      date.setTime(time)
      dateFormatter.setTimeZone(TimeZone.getTimeZone("UTC"))
      val table = dynamoDB.getTable(tableName)

      val item = new Item().withPrimaryKey(tablePrimaryKeyName, bucketStart)
        .withString(tableEventTypeSecondaryKeyName, eventType)
        .withString(tableCreatedAtColumnName, createdAt)
        .withString(tableUpdatedAtColumnName, updatedAt)
        .withInt(tableCountColumnName, count)

      // Saving the data to DynamoDB AggregrateRecords table
      table.putItem(item)
    } catch {
      case e: Exception => {
        System.err.println("Failed to create item in " + tableName)
        System.err.println(e.getMessage)
      }
    }
  }
}