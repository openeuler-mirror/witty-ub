#include "urma_failure_510.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure510> g_urma("urma_510");

bool UrmaFailure510::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_del_jetty_p_vjetty_info_without_lock") != std::string::npos &&
           message.find("Failed to delete p_vjetty_id node: ret:") != std::string::npos &&
           message.find("pjetty_id:") != std::string::npos;
}

std::string UrmaFailure510::GetName() const
{
    return "下层资源删除失败导致delDEL、Jetty、vjetty失败";
}

std::string UrmaFailure510::GetRootCauseDesc() const
{
    return "bondp_del_jetty_p_vjetty_info_without_"
           "lock清理DEL、Jetty、vjetty时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure510::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure510::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure510::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_del_jetty_p_vjetty_info_without_lock，Failed to delete "
           "p_vjetty_id node:"
           " ret:，pjetty_id:。";
}

std::string UrmaFailure510::GetId() const
{
    return "urma_510";
}
} // namespace diag
