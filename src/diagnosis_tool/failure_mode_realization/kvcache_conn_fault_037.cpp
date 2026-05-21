#include "kvcache_conn_fault_037.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault037> g_KvcacheConnFault037("kvcache_conn_fault_037");

KvcacheConnFault037::KvcacheConnFault037() noexcept
{
}

bool KvcacheConnFault037::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L690-L703
    // 来源: 08-fault-triage-consolidated.md L86-L89
    // 验证方法: KVCache错误码为5(K_RUNTIME_ERROR)且需按日志串细分
    // 匹配逻辑: 在uniq -c输出中，第二列(code)有5
    std::string uniqOutput = kvcache_conn_utils::RunCommand(
        R"(grep "DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c)");
    return kvcache_conn_utils::HasCodeInUniqOutput(uniqOutput, {5});
}

std::string KvcacheConnFault037::GetName() const
{
    return "code=5按日志串细分";
}

std::string KvcacheConnFault037::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause KvcacheConnFault037::AnalyzeRootCause()
{
    return RootCause(true, "向下级匹配。");
}

std::string KvcacheConnFault037::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string KvcacheConnFault037::GetValidationMethodDesc() const
{
    return "KVCache错误码为5(K_RUNTIME_ERROR)且需按日志串细分";
}

std::string KvcacheConnFault037::GetId() const
{
    return "kvcache_conn_fault_037";
}

} // namespace diag