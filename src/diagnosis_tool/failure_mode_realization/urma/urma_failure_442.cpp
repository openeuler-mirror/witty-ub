#include "urma_failure_442.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure442> g_urma("urma_442");

bool UrmaFailure442::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_alloc_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'alloc_jetty failed'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure442::GetName() const
{
    return "urma_alloc_jetty 分配 Jetty 临时参数失败导致分配流程无法继续";
}

std::string UrmaFailure442::GetRootCauseDesc() const
{
    return "urma_alloc_jetty 需要为 Jetty 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider "
           "调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。";
}

RootCause UrmaFailure442::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure442::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure442::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：alloc_jetty failed";
}

std::string UrmaFailure442::GetId() const
{
    return "urma_442";
}

} // namespace diag
