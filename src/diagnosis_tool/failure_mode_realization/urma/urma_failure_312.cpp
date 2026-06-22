#include "urma_failure_312.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure312> g_urma("urma_312");

bool UrmaFailure312::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_delete_vseg") != std::string::npos &&
           message.find("Failed to unregister segment, token_id:") != std::string::npos &&
           message.find(", handle:") != std::string::npos;
}

std::string UrmaFailure312::GetName() const
{
    return "下层注册或导入返回失败导致删除VSEG失败";
}

std::string UrmaFailure312::GetRootCauseDesc() const
{
    return "bondp_delete_vseg在删除VSEG时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure312::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure312::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure312::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_vseg，Failed to unregister segment, token_id:，, handle:。";
}

std::string UrmaFailure312::GetId() const
{
    return "urma_312";
}
} // namespace diag
