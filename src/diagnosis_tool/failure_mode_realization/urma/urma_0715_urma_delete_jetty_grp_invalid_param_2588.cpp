#include "urma_0715_urma_delete_jetty_grp_invalid_param_2588.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0715UrmaDeleteJettyGrpInvalidParam2588> g_urma("urma_0715");

bool Urma0715UrmaDeleteJettyGrpInvalidParam2588::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter: jetty_list"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0715UrmaDeleteJettyGrpInvalidParam2588::GetName() const
{
    return "urma_delete_jetty_grp 参数非法（日志行2588）";
}

std::string Urma0715UrmaDeleteJettyGrpInvalidParam2588::GetRootCauseDesc() const
{
    return "函数参数校验失败；该路径返回 URMA_EINVAL";
}

RootCause Urma0715UrmaDeleteJettyGrpInvalidParam2588::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0715UrmaDeleteJettyGrpInvalidParam2588::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0715UrmaDeleteJettyGrpInvalidParam2588::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter: jetty_list";
}

std::string Urma0715UrmaDeleteJettyGrpInvalidParam2588::GetId() const
{
    return "urma_0715";
}
} // namespace diag
