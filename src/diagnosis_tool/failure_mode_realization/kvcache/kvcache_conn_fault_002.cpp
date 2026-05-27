#include "kvcache_conn_fault_002.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_002
// 来源: kvcache_conn_fault_mode.md:L93, L127-189
static AutoRegister<KvcacheConnFault002> g_kvcacheconnfault002("kvcache_conn_fault_002");

bool KvcacheConnFault002::IsValid()
{
    // 提取status_code为2/3/8或code=0且respMsg异常的access log行。
    std::string rawOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG\" && "
        "awk -F'|' 'NR>0 {"
        "code=$8; action=$9; resp=$13; "
        "gsub(/^ +| +$/,\"\",code); "
        "gsub(/^ +| +$/,\"\",action); "
        "gsub(/^ +| +$/,\"\",resp)"
        "} action ~ /^DS_KV_CLIENT_(PUT|GET)$/ && "
        "(code == \"2\" || code == \"3\" || code == \"8\" || (code == \"0\" && resp != \"\")) "
        "{print $0}' $WITTY_UB_CLIENT_ACCESS_LOG 2>/dev/null");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    rawOutput = kvcache_log_helper::StripFilepathPrefixFromOutput(rawOutput);
    kvcache_log_helper::ParseFailureLogLine(rawOutput, logInfo);
    return !rawOutput.empty();
}

std::string KvcacheConnFault002::GetName() const
{
    // 来源: kvcache_conn_fault_mode.md:L93, L127-189
    return "用户侧错误（code=0/respMsg异常 + code=2/3/8）";
}

std::string KvcacheConnFault002::GetRootCauseDesc() const
{
    // 来源: kvcache_conn_fault_mode.md:L93, L127-189
    return "向下级匹配。";
}

RootCause KvcacheConnFault002::AnalyzeRootCause()
{
    // 来源: kvcache_conn_fault_mode.md:L93, L127-189
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault002::GetFixSuggDesc() const
{
    // 来源: kvcache_conn_fault_mode.md:L93, L127-189
    return "向下级匹配。";
}

std::string KvcacheConnFault002::GetValidationMethodDesc() const
{
    // 来源: kvcache_conn_fault_mode.md:L93, L127-189
    return "通过access log识别（来源：08手册:L127-130, L187-190）："
           "查询access log respMsg，code=0配合respMsg异常、"
           "或code=2(K_INVALID)/3(K_NOT_FOUND)/8(K_NOT_READY)。";
}

std::string KvcacheConnFault002::GetId() const
{
    return "kvcache_conn_fault_002";
}

} // namespace diag
