#include "urma_failure_547.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure547> g_urma("urma_547");

bool UrmaFailure547::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'post_send_check_valid' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Try to call post_send api by invalid comp_type:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure547::GetName() const
{
    return "WR对象无效导致投递组件失败";
}

std::string UrmaFailure547::GetRootCauseDesc() const
{
    return "函数用于投递组件，调用方传入的WR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure547::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure547::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure547::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：post_send_check_valid，Try to call post_send api by invalid comp_type:";
}

std::string UrmaFailure547::GetId() const
{
    return "urma_547";
}

} // namespace diag
