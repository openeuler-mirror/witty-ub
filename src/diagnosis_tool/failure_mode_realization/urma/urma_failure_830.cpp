#include "urma_failure_830.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure830> g_urma("urma_830");

bool UrmaFailure830::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_deactive_jfr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure830::GetName() const
{
    return "provider操作表、JFR对象无效导致去激活JFR失败";
}

std::string UrmaFailure830::GetRootCauseDesc() const
{
    return "函数用于去激活JFR，调用方传入的provider操作表、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure830::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure830::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure830::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_deactive_jfr，Invalid parameter.。";
}

std::string UrmaFailure830::GetId() const
{
    return "urma_830";
}

} // namespace diag
