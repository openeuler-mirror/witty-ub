#include "urma_failure_355.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure355> g_urma("urma_355");

bool UrmaFailure355::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_delete_pjfce") != std::string::npos &&
           message.find("Failed to delete pjfce") != std::string::npos && message.find(", ret:") != std::string::npos;
}

std::string UrmaFailure355::GetName() const
{
    return "下层资源删除失败导致删除物理JFCE失败";
}

std::string UrmaFailure355::GetRootCauseDesc() const
{
    return "bondp_delete_pjfce清理物理JFCE时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure355::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure355::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure355::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_pjfce，Failed to delete pjfce，, ret:。";
}

std::string UrmaFailure355::GetId() const
{
    return "urma_355";
}
} // namespace diag
