#include "urma_failure_691.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure691> g_urma("urma_691");

bool UrmaFailure691::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_net_addr_list' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure691::GetName() const
{
    return "释放URMA资源所需输入对象无效导致释放URMA资源失败";
}

std::string UrmaFailure691::GetRootCauseDesc() const
{
    return "函数用于释放URMA资源，调用方传入的释放URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure691::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure691::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure691::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_net_addr_list，Invalid parameter.。";
}

std::string UrmaFailure691::GetId() const
{
    return "urma_691";
}

} // namespace diag
