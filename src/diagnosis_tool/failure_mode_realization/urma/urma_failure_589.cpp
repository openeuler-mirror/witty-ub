#include "urma_failure_589.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure589> g_urma("urma_589");

bool UrmaFailure589::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_post_jfr_wr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure589::GetName() const
{
    return "JFR对象、WR对象无效导致投递JFR失败";
}

std::string UrmaFailure589::GetRootCauseDesc() const
{
    return "函数用于投递JFR，调用方传入的JFR对象、WR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure589::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure589::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure589::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_post_jfr_wr，Invalid parameter.。";
}

std::string UrmaFailure589::GetId() const
{
    return "urma_589";
}

} // namespace diag
