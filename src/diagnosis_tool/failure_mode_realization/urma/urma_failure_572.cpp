#include "urma_failure_572.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure572> g_urma("urma_572");

bool UrmaFailure572::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_unregister_seg' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'bondp_hash_table_lookup fail')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure572::GetName() const
{
    return "bondp_unregister_seg 装载或匹配 provider 失败导致设备驱动能力不可用";
}

std::string UrmaFailure572::GetRootCauseDesc() const
{
    return "bondp_unregister_seg 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 "
           "provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。";
}

RootCause UrmaFailure572::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure572::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure572::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：bondp_hash_table_lookup fail";
}

std::string UrmaFailure572::GetId() const
{
    return "urma_572";
}

} // namespace diag
