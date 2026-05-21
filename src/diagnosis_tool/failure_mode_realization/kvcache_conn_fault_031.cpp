#include "kvcache_conn_fault_031.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault031> g_KvcacheConnFault031("kvcache_conn_fault_031");

KvcacheConnFault031::KvcacheConnFault031() noexcept
{
}

bool KvcacheConnFault031::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L563-L572
    // 来源: 08-fault-triage-consolidated.md L73-L74
    // 来源: 10-customer-fault-scenarios.md L78-L80
    // 验证方法: KVCache错误码为5(K_RUNTIME_ERROR)、6(K_OUT_OF_MEMORY)、7(K_IO_ERROR)、13(K_NO_SPACE)或18(K_FILE_LIMIT_REACHED)
    // 匹配逻辑: 在uniq -c输出中，第二列(code)有5, 6, 7, 13, 18
    std::string uniqOutput = kvcache_conn_utils::RunCommand(
        R"(grep "DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c)");
    return kvcache_conn_utils::HasCodeInUniqOutput(uniqOutput, {5, 6, 7, 13, 18});
}

std::string KvcacheConnFault031::GetName() const
{
    return "OS错误";
}

std::string KvcacheConnFault031::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause KvcacheConnFault031::AnalyzeRootCause()
{
    return RootCause(false, "向下级匹配。");
}

std::string KvcacheConnFault031::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string KvcacheConnFault031::GetValidationMethodDesc() const
{
    return "KVCache错误码为5(K_RUNTIME_ERROR)、6(K_OUT_OF_MEMORY)、7(K_IO_ERROR)、13(K_NO_SPACE)或18(K_FILE_LIMIT_REACHED)";
}

std::string KvcacheConnFault031::GetId() const
{
    return "kvcache_conn_fault_031";
}

} // namespace diag