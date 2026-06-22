#include "urma_failure_363.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure363> g_urma("urma_363");

bool UrmaFailure363::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_delete_pjfc") != std::string::npos &&
           message.find("Failed to delete pjfc") != std::string::npos && message.find(", ret:") != std::string::npos;
}

std::string UrmaFailure363::GetName() const
{
    return "下层资源删除失败导致删除物理JFC失败";
}

std::string UrmaFailure363::GetRootCauseDesc() const
{
    return "bondp_delete_pjfc清理物理JFC时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure363::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure363::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure363::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_pjfc，Failed to delete pjfc，, ret:。";
}

std::string UrmaFailure363::GetId() const
{
    return "urma_363";
}
} // namespace diag
