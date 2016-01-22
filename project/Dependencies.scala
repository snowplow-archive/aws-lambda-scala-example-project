/*
 * Copyright (c) 2012-2015 Snowplow Analytics Ltd. All rights reserved.
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

import sbt._

object Dependencies {

  object V {
    val awsLambda = "1.0.0"
    val awsSdk = "1.9.34"
    val jackson = "2.5.2"
    val json4s = "3.2.11"
    val awscala = "0.5.+"
  }

  object Libraries {
    val awsLambda = "com.amazonaws" % "aws-lambda-java-core" % V.awsLambda
    val awsLambdaEvents = "com.amazonaws" % "aws-lambda-java-events" % V.awsLambda
    val awsSdk = "com.amazonaws" % "aws-java-sdk" % V.awsSdk % "provided"
    val awsSdkCore = "com.amazonaws" % "aws-java-sdk-core" % V.awsSdk % "provided"
    val jackson = "com.fasterxml.jackson.module" % "jackson-module-scala_2.11" % V.jackson
    val json4s = "org.json4s" %% "json4s-jackson" % V.json4s
    val awsscala = "com.github.seratch" %% "awscala" % V.awscala
  }

}
