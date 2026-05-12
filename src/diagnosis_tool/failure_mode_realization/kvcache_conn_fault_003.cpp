#include "kvcache_conn_fault_003.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault003> g_KvcacheConnFault003("kvcache_conn_fault_003");

KvcacheConnFault003::KvcacheConnFault003() noexcept
{
}

bool KvcacheConnFault003::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L110-L127
    // 来源: 08-fault-triage-consolidated.md L175-L176
    // 来源: 10-customer-fault-scenarios.md L127-L130
    // Case 1: access log中code=2且respMsg含参数校验失败描述
    // 来源: references/kvcache_conn_fault_mode.md L110-L127
    std::string accessOutput0 = kvcache_conn_utils::RunCommand(
        R"(grep '^2 |' $LOG/ds_client_access_*.log 2>/dev/null)");
    bool case0_matched = accessOutput0.find("The objectKey is empty") != std::string::npos || accessOutput0.find("dataSize should be bigger than zero") != std::string::npos || accessOutput0.find("length not match") != std::string::npos;
    // Case 2: INFO log含K_INVALID
    // 来源: references/kvcache_conn_fault_mode.md L110-L127
    std::string grepOutput1 = kvcache_conn_utils::RunCommand(
        R"(grep 'K_INVALID' $LOG/ds_client_*.INFO.log 2>/dev/null)");
    bool case1_matched = !grepOutput1.empty();
    return case0_matched || case1_matched;
}

std::string KvcacheConnFault003::GetName() const
{
    return "参数非法";
}

std::string KvcacheConnFault003::GetRootCauseDesc() const
{
    return "业务参数非法";
}

RootCause KvcacheConnFault003::AnalyzeRootCause()
{
    return RootCause(true, "业务参数非法");
}

std::string KvcacheConnFault003::GetFixSuggDesc() const
{
    return "业务校验";
}

std::string KvcacheConnFault003::GetValidationMethodDesc() const
{
    return "access log错误码为2(K_INVALID)或INFO log含K_INVALID及参数校验失败描述";
}

std::string KvcacheConnFault003::GetId() const
{
    return "kvcache_conn_fault_003";
}

} // namespace diag