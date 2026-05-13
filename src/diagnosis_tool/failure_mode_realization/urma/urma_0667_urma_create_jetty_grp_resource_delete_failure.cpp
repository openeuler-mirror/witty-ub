#include "urma_0667_urma_create_jetty_grp_resource_delete_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0667UrmaCreateJettyGrpResourceDeleteFailure> g_urma("urma_0667");

bool Urma0667UrmaCreateJettyGrpResourceDeleteFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"delete_jetty_grp failed."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0667UrmaCreateJettyGrpResourceDeleteFailure::GetName() const
{
    return "urma_create_jetty_grp 删除资源失败";
}

std::string Urma0667UrmaCreateJettyGrpResourceDeleteFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "NULL";
}

RootCause Urma0667UrmaCreateJettyGrpResourceDeleteFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0667UrmaCreateJettyGrpResourceDeleteFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0667UrmaCreateJettyGrpResourceDeleteFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：delete_jetty_grp failed.";
}

std::string Urma0667UrmaCreateJettyGrpResourceDeleteFailure::GetId() const
{
    return "urma_0667";
}
} // namespace diag
