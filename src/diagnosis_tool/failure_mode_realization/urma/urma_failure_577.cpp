#include "urma_failure_577.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure577> g_urma("urma_577");

bool UrmaFailure577::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_import_seg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to lookup v2p_token_id, ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure577::GetName() const
{
    return "bondp_import_seg 装载或匹配 provider 失败导致设备驱动能力不可用";
}

std::string UrmaFailure577::GetRootCauseDesc() const
{
    return "bondp_import_seg 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider "
           "注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。";
}

RootCause UrmaFailure577::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure577::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure577::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to lookup v2p_token_id, ret";
}

std::string UrmaFailure577::GetId() const
{
    return "urma_577";
}

} // namespace diag
