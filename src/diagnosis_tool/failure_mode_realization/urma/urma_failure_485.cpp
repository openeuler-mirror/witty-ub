#include "urma_failure_485.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure485> g_urma("urma_485");

bool UrmaFailure485::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_create_context' "$URMA_LOG_PATH" 2>/dev/null | grep -F '[DRV_ERR]Failed to create urma context')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure485::GetName() const
{
    return "urma_create_context 装载或匹配 provider 失败导致设备驱动能力不可用";
}

std::string UrmaFailure485::GetRootCauseDesc() const
{
    return "urma_create_context 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 "
           "provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。";
}

RootCause UrmaFailure485::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure485::GetFixSuggDesc() const
{
    return "当前不会触发";
}

std::string UrmaFailure485::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：[DRV_ERR]Failed to create urma context";
}

std::string UrmaFailure485::GetId() const
{
    return "urma_485";
}

} // namespace diag
