#include "urma_failure_543.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure543> g_urma("urma_543");

bool UrmaFailure543::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'comp_post_recv' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid post jfr wr type:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure543::GetName() const
{
    return "JFR对象、WR对象无效导致投递JFR失败";
}

std::string UrmaFailure543::GetRootCauseDesc() const
{
    return "函数用于投递JFR，调用方传入的JFR对象、WR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure543::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure543::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure543::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：comp_post_recv，Invalid post jfr wr type:";
}

std::string UrmaFailure543::GetId() const
{
    return "urma_543";
}

} // namespace diag
