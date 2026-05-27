#include "urma_failure_671.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure671> g_urma("urma_671");

bool UrmaFailure671::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_jfr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure671::GetName() const
{
    return "URMA context、provider操作表、JFR对象无效导致释放JFR失败";
}

std::string UrmaFailure671::GetRootCauseDesc() const
{
    return "函数用于释放JFR，调用方传入的URMA "
           "context、provider操作表、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure671::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure671::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure671::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_jfr，Invalid parameter.。";
}

std::string UrmaFailure671::GetId() const
{
    return "urma_671";
}

} // namespace diag
