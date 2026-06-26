#include "kvcache_conn_fault_012_004.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault012_004> g_kvcacheconnfault("kvcache_conn_fault_012_004");

bool KvcacheConnFault012_004::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return (message.find("Cannot receive heartbeat from worker") != std::string::npos ||
            message.find("[HealthCheck] Worker is exiting now") != std::string::npos ||
            message.find("meta_is_moving") != std::string::npos);
}

std::string KvcacheConnFault012_004::GetName() const
{
    return "心跳/生命周期/扩缩容。";
}

std::string KvcacheConnFault012_004::GetRootCauseDesc() const
{
    return "分为三种情况（08手册:L274）：心跳断kill -CONT恢复；退出由编排自动拉起；"
           "扩缩容SDK自重试。";
}

RootCause KvcacheConnFault012_004::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault012_004::GetFixSuggDesc() const
{
    return "心跳断→kill -CONT <pid>；退出由编排拉起；扩缩容SDK自重试（08手册:L274）。";
}

std::string KvcacheConnFault012_004::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L274）：匹配Cannot receive "
           "heartbeat from worker / [HealthCheck] Worker is exiting now / meta_is_moving "
           "= true。";
}

std::string KvcacheConnFault012_004::GetId() const
{
    return "kvcache_conn_fault_012_004";
}
} // namespace diag
