#include "kvcache_conn_fault_013.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault013> g_KvcacheConnFault013("kvcache_conn_fault_013");

KvcacheConnFault013::KvcacheConnFault013() noexcept
{
}

bool KvcacheConnFault013::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L260-L285
    // 来源: 08-fault-triage-consolidated.md L73-L74
    // 来源: 10-customer-fault-scenarios.md L161-L166
    // Case 1: 返回错误码中有25
    // 来源: references/kvcache_conn_fault_mode.md L260-L285
    std::string uniqOutput0 = kvcache_conn_utils::RunCommand(
        R"(grep "DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c)");
    bool case0_matched = kvcache_conn_utils::HasCodeInUniqOutput(uniqOutput0, {25});
    // Case 2: INFO log含etcd is timeout或etcd is unavailable
    // 来源: references/kvcache_conn_fault_mode.md L260-L285
    std::string grepOutput1 = kvcache_conn_utils::RunCommand(
        R"(grep -E 'etcd is timeout|etcd is unavailable' $LOG/*.INFO.log | tail -20 2>/dev/null)");
    bool case1_matched = !grepOutput1.empty();
    // Case 3: ETCD_QUEUE堆积或ETCD_REQUEST_SUCCESS_RATE下降
    // 来源: references/kvcache_conn_fault_mode.md L260-L285
    std::string resourceOut2 = kvcache_conn_utils::RunCommand(
        R"(grep 'ETCD_REQUEST_SUCCESS_RATE\|ETCD_QUEUE' $LOG/resource.log | tail -5 2>/dev/null)");
    // Warning: resource log check requires parsing ETCD_QUEUE_USAGE >= 80% or success rate < 0.95
    bool case2_matched = !resourceOut2.empty();
    return case0_matched || case1_matched || case2_matched;
}

std::string KvcacheConnFault013::GetName() const
{
    return "三方etcd错误";
}

std::string KvcacheConnFault013::GetRootCauseDesc() const
{
    return "etcd集群故障或到etcd的网络异常。主责三方etcd";
}

RootCause KvcacheConnFault013::AnalyzeRootCause()
{
    return RootCause(true, "etcd集群故障或到etcd的网络异常。主责三方etcd");
}

std::string KvcacheConnFault013::GetFixSuggDesc() const
{
    return "systemctl status etcd；etcdctl endpoint status -w table；查到etcd的网络";
}

std::string KvcacheConnFault013::GetValidationMethodDesc() const
{
    return "KVCache错误码为25(K_MASTER_TIMEOUT)或INFO log含etcd is timeout/unavailable或resource log含ETCD_QUEUE堆积";
}

std::string KvcacheConnFault013::GetId() const
{
    return "kvcache_conn_fault_013";
}

} // namespace diag