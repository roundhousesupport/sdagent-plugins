#!/usr/bin/env python

# Copyright (c) 2011, David Taylor
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
# Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# 
# Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
# 
# Neither the name of David Taylor, nor the names of its contributors
# may be used to endorse or promote products derived from this software
# without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

# h1. Adds Passenger Monitoring to Server Density
# 
# Installation
# 
# * Head to  https://youraccount.serverdensity.com/plugins/ and Add new plugin
# * Add a plugin called Passenger
# * Edit the Passenger plugin and enter these groups for the graphs:
# 
# Title: Status
# max_application_instances
# count_application_instances
# active_application_instances
# inactive_application_instances
# waiting_on_global_queue
# 
# Title: Processes
# processes
# 
# Title: Memory
# passenger_watchdog_rss_mb
# passenger_helper_agent_rss_mb
# passenger_spawn_server_rss_mb
# passenger_login_agent_rss_mb
# total_rss_mb
# 
# * Configure your agent so that it knows about plugins http://www.serverdensity.com/docs/agent/plugins/ 
# * Move Passenger.py into that directory 
# * Restart the agent (service sd-agent restart)


import re
import commands


# NB: These commands require the ability to run passenger-memory-stats and
# passenger-status.  You might need to prepend the commands with 'rvmsudo'
# or 'sudo -u username -i rvmsudo' or some other concoction.
#
# Removes colour codes from the output using:
# sed -r "s/\x1B\[([0-9]{1,3}((;[0-9]{1,3})*)?)?[m|K]//g"
PASSENGER_MEMORY_STATS_CMD = 'passenger-memory-stats | sed -r "s/\x1B\[([0-9]{1,3}((;[0-9]{1,3})*)?)?[m|K]//g"'
PASSENGER_STATUS_CMD = 'passenger-status | sed -r "s/\x1B\[([0-9]{1,3}((;[0-9]{1,3})*)?)?[m|K]//g"'


class Passenger:
    def __init__(self, agentConfig, checksLogger, rawConfig):
        self.agentConfig = agentConfig
        self.checksLogger = checksLogger
        self.rawConfig = rawConfig

    def run(self):
        stats = {}
        
        try:

          # Get passenger status.  Eg,
          #
          # max      = 40
          # count    = 40
          # active   = 0
          # inactive = 40
          # Waiting on global queue: 0
          status, out = commands.getstatusoutput(PASSENGER_STATUS_CMD)
          stats['max_application_instances'] = int(re.search('max += (\d+)', out).group(1))
          stats['count_application_instances'] = int(re.search('count += (\d+)', out).group(1))
          stats['active_application_instances'] = int(re.search('active += (\d+)', out).group(1))
          stats['inactive_application_instances'] = int(re.search('inactive += (\d+)', out).group(1))
          stats['waiting_on_global_queue'] = int(re.search('Waiting on global queue: (\d+)', out).group(1))

          # Get passenger memory stats.  Eg,
          #
          # 20998  22.9 MB   0.3 MB   PassengerWatchdog
          # 21001  126.4 MB  6.8 MB   PassengerHelperAgent
          # 21004  46.1 MB   8.3 MB   Passenger spawn server
          # 21016  70.5 MB   0.8 MB   PassengerLoggingAgent
          status, out = commands.getstatusoutput(PASSENGER_MEMORY_STATS_CMD)
          stats['passenger_watchdog_rss_mb'] = float(re.search('\d+ +\d+\.?\d+ MB +(\d+\.?\d+) MB + PassengerWatchdog', out).group(1))
          stats['passenger_helper_agent_rss_mb'] = float(re.search('\d+ +\d+\.?\d+ MB +(\d+\.?\d+) MB + PassengerHelperAgent', out).group(1))
          stats['passenger_spawn_server_rss_mb'] = float(re.search('\d+ +\d+\.?\d+ MB +(\d+\.?\d+) MB + Passenger spawn server', out).group(1))
          stats['passenger_logging_agent_rss_mb'] = float(re.search('\d+ +\d+\.?\d+ MB +(\d+\.?\d+) MB + PassengerLoggingAgent', out).group(1))
          # There are multiple sections, each with lines that match
          # the regex for totals, so we scan down to the section we're
          # interested in
          in_passenger_processes = False
          stats['processes'] = None
          stats['total_rss_mb'] = None
          for line in out.splitlines():
              # Make sure we jump past the sections about Apache and Nginx,
              # straight to the Passenger section
              if not in_passenger_processes:
                  in_passenger_processes = re.match('-+ Passenger processes -+', line)
                  continue
              # Total number of passenger processes.  Eg,
              # ### Processes: 44
              processes_match = re.match('### Processes: (\d+)', line)
              if processes_match:
                  stats['processes'] = int(processes_match.group(1))
              # Total RSS used by passenger and rails processes.  Eg,
              # ### Total private dirty RSS: 2266.23 MB
              total_rss_mb_match = re.match('### Total private dirty RSS: (\d+\.?\d+) MB', line)
              if total_rss_mb_match:
                  stats['total_rss_mb'] = float(total_rss_mb_match.group(1))
        finally:        
          return stats


if __name__ == "__main__":
    passenger = Passenger(None, None, None)
    print passenger.run()