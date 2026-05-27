#include "urma_failure_843.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure843> g_urma("urma_843");

bool UrmaFailure843::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_seg_cfg' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure843::GetName() const
{
    return "URMA context、provider操作表、Segment对象无效导致注册Segment失败";
}

std::string UrmaFailure843::GetRootCauseDesc() const
{
    return "函数用于注册Segment，调用方传入的URMA "
           "context、provider操作表、Segment对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure843::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure843::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure843::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_check_seg_cfg，Invalid parameter.。";
}

std::string UrmaFailure843::GetId() const
{
    return "urma_843";
}

} // namespace diag
