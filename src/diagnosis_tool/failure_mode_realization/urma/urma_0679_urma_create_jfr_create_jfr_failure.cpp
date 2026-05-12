#include "urma_0679_urma_create_jfr_create_jfr_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0679UrmaCreateJfrCreateJfrFailure> g_urma("urma_0679");

bool Urma0679UrmaCreateJfrCreateJfrFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"[DRV_ERR]Failed to create jfr, dev_name: %, eid_idex: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0679UrmaCreateJfrCreateJfrFailure::GetName() const
{
    return "urma_create_jfr 创建JFR失败";
}

std::string Urma0679UrmaCreateJfrCreateJfrFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 jfr";
}

RootCause Urma0679UrmaCreateJfrCreateJfrFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0679UrmaCreateJfrCreateJfrFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0679UrmaCreateJfrCreateJfrFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：[DRV_ERR]Failed to create jfr, dev_name: %, eid_idex: %.";
}

std::string Urma0679UrmaCreateJfrCreateJfrFailure::GetId() const
{
    return "urma_0679";
}
} // namespace diag
