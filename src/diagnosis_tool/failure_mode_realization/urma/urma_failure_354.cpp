#include "urma_failure_354.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure354> g_urma("urma_354");

bool UrmaFailure354::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'update_mapping_hash_table' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid topo info to create topo map'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure354::GetName() const
{
    return "执行URMA资源所需输入对象无效导致创建URMA资源失败";
}

std::string UrmaFailure354::GetRootCauseDesc() const
{
    return "函数用于创建URMA资源，调用方传入的执行URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure354::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure354::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure354::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：update_mapping_hash_table，Invalid topo info to create topo map。";
}

std::string UrmaFailure354::GetId() const
{
    return "urma_354";
}

} // namespace diag
