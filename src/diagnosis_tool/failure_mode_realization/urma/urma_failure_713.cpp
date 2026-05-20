#include "urma_failure_713.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure713> g_urma("urma_713");

bool UrmaFailure713::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_delete_comp_default' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Fail to uninit comp attr, ret'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure713::GetName() const
{
    return "bondp_delete_comp_default 装载或匹配 provider 失败导致设备驱动能力不可用";
}

std::string UrmaFailure713::GetRootCauseDesc() const
{
    return "bondp_delete_comp_default 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 "
           "provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。";
}

RootCause UrmaFailure713::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure713::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure713::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Fail to uninit comp attr, ret";
}

std::string UrmaFailure713::GetId() const
{
    return "urma_713";
}

} // namespace diag
