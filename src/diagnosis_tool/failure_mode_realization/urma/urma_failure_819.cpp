#include "urma_failure_819.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure819> g_urma("urma_819");

bool UrmaFailure819::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_jfr_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure819::GetName() const
{
    return "URMA context、provider操作表、JFR对象无效导致设置JFR失败";
}

std::string UrmaFailure819::GetRootCauseDesc() const
{
    return "函数用于设置JFR，调用方传入的URMA "
           "context、provider操作表、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure819::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure819::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure819::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jfr_opt，Invalid parameter.。";
}

std::string UrmaFailure819::GetId() const
{
    return "urma_819";
}

} // namespace diag
