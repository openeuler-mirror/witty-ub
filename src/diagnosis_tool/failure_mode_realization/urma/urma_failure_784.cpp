#include "urma_failure_784.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure784> g_urma("urma_784");

bool UrmaFailure784::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_deactive_jfc' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure784::GetName() const
{
    return "provider操作表无效导致去激活JFC失败";
}

std::string UrmaFailure784::GetRootCauseDesc() const
{
    return "函数用于去激活JFC，调用方传入的provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure784::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure784::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure784::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_deactive_jfc，Invalid parameter.。";
}

std::string UrmaFailure784::GetId() const
{
    return "urma_784";
}

} // namespace diag
