#include "urma_failure_308.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure308> g_urma("urma_308");

bool UrmaFailure308::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_delete_pseg") != std::string::npos &&
           message.find("Failed to unregister pseg") != std::string::npos;
}

std::string UrmaFailure308::GetName() const
{
    return "下层注册或导入返回失败导致删除PSEG失败";
}

std::string UrmaFailure308::GetRootCauseDesc() const
{
    return "bondp_delete_pseg在删除PSEG时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure308::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure308::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure308::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_pseg，Failed to unregister pseg。";
}

std::string UrmaFailure308::GetId() const
{
    return "urma_308";
}
} // namespace diag
