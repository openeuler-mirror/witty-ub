#include "urma_0548_urma_cmd_set_jfr_opt_jfc_not_exist_jfr.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0548UrmaCmdSetJfrOptJfcNotExistJfr> g_urma("urma_0548");

bool Urma0548UrmaCmdSetJfrOptJfcNotExistJfr::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"jfc not exist in jfr."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0548UrmaCmdSetJfrOptJfcNotExistJfr::GetName() const
{
    return "urma_cmd_set_jfr_opt jfc not exist in jfr.";
}

std::string Urma0548UrmaCmdSetJfrOptJfcNotExistJfr::GetRootCauseDesc() const
{
    return "目标文件、设备节点或动态库打开失败，可能由于路径不存在、权限不足或 provider/设备文件不可访问；该路径返回 "
           "-1";
}

RootCause Urma0548UrmaCmdSetJfrOptJfcNotExistJfr::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0548UrmaCmdSetJfrOptJfcNotExistJfr::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0548UrmaCmdSetJfrOptJfcNotExistJfr::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jfc not exist in jfr.";
}

std::string Urma0548UrmaCmdSetJfrOptJfcNotExistJfr::GetId() const
{
    return "urma_0548";
}
} // namespace diag
