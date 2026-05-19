#include "urma_failure_272.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure272> g_urma("urma_272");

bool UrmaFailure272::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_create_vseg' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Fail to register vseg, ret:')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure272::GetName() const
{
    return "bondp_create_vseg 装载或匹配 provider 失败导致设备驱动能力不可用";
}

std::string UrmaFailure272::GetRootCauseDesc() const
{
    return "bondp_create_vseg 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 "
           "provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。";
}

RootCause UrmaFailure272::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure272::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure272::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Fail to register vseg, ret";
}

std::string UrmaFailure272::GetId() const
{
    return "urma_272";
}

} // namespace diag
