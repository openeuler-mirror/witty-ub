#include "urma_failure_529.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure529> g_urma("urma_529");

bool UrmaFailure529::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_unregister_seg' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure529::GetName() const
{
    return "URMA context无效导致注销Segment失败";
}

std::string UrmaFailure529::GetRootCauseDesc() const
{
    return "函数用于注销Segment，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure529::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure529::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure529::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_unregister_seg，Invalid parameter。";
}

std::string UrmaFailure529::GetId() const
{
    return "urma_529";
}

} // namespace diag
