#include "urma_1107_urma_check_seg_cfg_atomic_access_should_be_config_with.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1107UrmaCheckSegCfgAtomicAccessShouldBeConfigWith> g_urma("urma_1107");

bool Urma1107UrmaCheckSegCfgAtomicAccessShouldBeConfigWith::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Atomic access should be config with read and write access."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1107UrmaCheckSegCfgAtomicAccessShouldBeConfigWith::GetName() const
{
    return "urma_check_seg_cfg Atomic access should be config with";
}

std::string Urma1107UrmaCheckSegCfgAtomicAccessShouldBeConfigWith::GetRootCauseDesc() const
{
    return "读取 sysfs 或设备文件失败，可能由于设备未注册、路径不存在、权限不足或读取返回异常；该路径返回 false";
}

RootCause Urma1107UrmaCheckSegCfgAtomicAccessShouldBeConfigWith::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1107UrmaCheckSegCfgAtomicAccessShouldBeConfigWith::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1107UrmaCheckSegCfgAtomicAccessShouldBeConfigWith::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Atomic access should be config with read and write access.";
}

std::string Urma1107UrmaCheckSegCfgAtomicAccessShouldBeConfigWith::GetId() const
{
    return "urma_1107";
}
} // namespace diag
