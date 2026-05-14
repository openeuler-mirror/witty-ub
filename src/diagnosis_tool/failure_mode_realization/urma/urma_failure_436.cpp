#include "urma_failure_436.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure436> g_urma("urma_436");

bool UrmaFailure436::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_import_jetty_async' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to alloc incomplete_tjetty')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure436::GetName() const
{
    return "urma_import_jetty_async 分配 目标 Jetty 临时参数失败导致导入流程无法继续";
}

std::string UrmaFailure436::GetRootCauseDesc() const
{
    return "urma_import_jetty_async 需要为 目标 Jetty 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 "
           "provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。";
}

RootCause UrmaFailure436::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure436::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure436::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to alloc incomplete_tjetty";
}

std::string UrmaFailure436::GetId() const
{
    return "urma_436";
}

} // namespace diag
