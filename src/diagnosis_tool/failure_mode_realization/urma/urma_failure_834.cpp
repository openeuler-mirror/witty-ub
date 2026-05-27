#include "urma_failure_834.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure834> g_urma("urma_834");

bool UrmaFailure834::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_seg_cfg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure834::GetName() const
{
    return "URMA context、provider操作表、Segment对象无效导致注册Segment失败";
}

std::string UrmaFailure834::GetRootCauseDesc() const
{
    return "函数用于注册Segment，调用方传入的URMA "
           "context、provider操作表、Segment对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure834::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure834::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure834::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_check_seg_cfg，Invalid parameter.";
}

std::string UrmaFailure834::GetId() const
{
    return "urma_834";
}

} // namespace diag
