#include "urma_failure_505.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure505> g_urma("urma_505");

bool UrmaFailure505::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_del_jfr_p_vjetty_info_without_lock") != std::string::npos &&
           message.find("Failed to delete p_vjfr_id node[") != std::string::npos &&
           message.find("]: ret") != std::string::npos && message.find("pjfr_id:") != std::string::npos;
}

std::string UrmaFailure505::GetName() const
{
    return "下层资源删除失败导致delDEL、JFR、vjetty失败";
}

std::string UrmaFailure505::GetRootCauseDesc() const
{
    return "bondp_del_jfr_p_vjetty_info_without_"
           "lock清理DEL、JFR、vjetty时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure505::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure505::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure505::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_del_jfr_p_vjetty_info_without_lock，Failed to delete p_vjfr_id "
           "node[，]: "
           "ret，pjfr_id:。";
}

std::string UrmaFailure505::GetId() const
{
    return "urma_505";
}
} // namespace diag
