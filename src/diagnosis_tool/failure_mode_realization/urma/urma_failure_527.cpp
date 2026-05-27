#include "urma_failure_527.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure527> g_urma("urma_527");

bool UrmaFailure527::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_register_seg' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure527::GetName() const
{
    return "URMA context无效导致注册Segment失败";
}

std::string UrmaFailure527::GetRootCauseDesc() const
{
    return "函数用于注册Segment，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure527::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure527::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure527::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_register_seg，Invalid parameter。";
}

std::string UrmaFailure527::GetId() const
{
    return "urma_527";
}

} // namespace diag
