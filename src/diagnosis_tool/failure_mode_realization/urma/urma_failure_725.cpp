#include "urma_failure_725.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure725> g_urma("urma_725");

bool UrmaFailure725::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bdp_slide_wnd_seq_in_window' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid param wnd'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure725::GetName() const
{
    return "执行URMA资源所需输入对象无效导致释放URMA资源失败";
}

std::string UrmaFailure725::GetRootCauseDesc() const
{
    return "函数用于释放URMA资源，调用方传入的执行URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure725::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure725::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure725::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bdp_slide_wnd_seq_in_window，Invalid param wnd";
}

std::string UrmaFailure725::GetId() const
{
    return "urma_725";
}

} // namespace diag
