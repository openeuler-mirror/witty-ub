#include "urma_failure_201.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure201> g_urma("urma_201");

bool UrmaFailure201::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_import_jetty' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to alloc target jetty')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure201::GetName() const
{
    return "bondp_import_jetty 分配 目标 Jetty 临时参数失败导致导入流程无法继续";
}

std::string UrmaFailure201::GetRootCauseDesc() const
{
    return "bondp_import_jetty 需要为 目标 Jetty 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider "
           "调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。";
}

RootCause UrmaFailure201::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure201::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure201::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to alloc target jetty";
}

std::string UrmaFailure201::GetId() const
{
    return "urma_201";
}

} // namespace diag
