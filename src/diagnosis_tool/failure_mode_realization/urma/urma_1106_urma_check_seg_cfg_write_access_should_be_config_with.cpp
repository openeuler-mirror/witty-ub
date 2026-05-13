#include "urma_1106_urma_check_seg_cfg_write_access_should_be_config_with.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1106UrmaCheckSegCfgWriteAccessShouldBeConfigWith> g_urma("urma_1106");

bool Urma1106UrmaCheckSegCfgWriteAccessShouldBeConfigWith::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Write access should be config with read access."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1106UrmaCheckSegCfgWriteAccessShouldBeConfigWith::GetName() const
{
    return "urma_check_seg_cfg Write access should be config with r";
}

std::string Urma1106UrmaCheckSegCfgWriteAccessShouldBeConfigWith::GetRootCauseDesc() const
{
    return "读取 sysfs 或设备文件失败，可能由于设备未注册、路径不存在、权限不足或读取返回异常；该路径返回 false";
}

RootCause Urma1106UrmaCheckSegCfgWriteAccessShouldBeConfigWith::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1106UrmaCheckSegCfgWriteAccessShouldBeConfigWith::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1106UrmaCheckSegCfgWriteAccessShouldBeConfigWith::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Write access should be config with read access.";
}

std::string Urma1106UrmaCheckSegCfgWriteAccessShouldBeConfigWith::GetId() const
{
    return "urma_1106";
}
} // namespace diag
