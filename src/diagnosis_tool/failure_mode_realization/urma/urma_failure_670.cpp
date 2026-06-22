#include "urma_failure_670.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure670> g_urma("urma_670");

bool UrmaFailure670::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_modify_jetty") != std::string::npos &&
           message.find("modify pjetty fail, index:") != std::string::npos &&
           message.find(", ret:") != std::string::npos;
}

std::string UrmaFailure670::GetName() const
{
    return "修改Jetty执行失败导致修改Jetty失败";
}

std::string UrmaFailure670::GetRootCauseDesc() const
{
    return "bondp_modify_jetty执行修改Jetty时依赖的修改Jetty步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure670::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure670::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure670::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_modify_jetty，modify pjetty fail, index:，, ret:。";
}

std::string UrmaFailure670::GetId() const
{
    return "urma_670";
}
} // namespace diag
