#include "urma_failure_032.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure032> g_urma("urma_032");

bool UrmaFailure032::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bdp_slide_wnd_init' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid param: total_size <= window_size'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure032::GetName() const
{
    return "初始化URMA资源所需输入对象无效导致初始化URMA资源失败";
}

std::string UrmaFailure032::GetRootCauseDesc() const
{
    return "函数用于初始化URMA资源，调用方传入的初始化URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作"
           "。";
}

RootCause UrmaFailure032::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure032::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure032::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bdp_slide_wnd_init，Invalid param: total_size <= window_size";
}

std::string UrmaFailure032::GetId() const
{
    return "urma_032";
}

} // namespace diag
