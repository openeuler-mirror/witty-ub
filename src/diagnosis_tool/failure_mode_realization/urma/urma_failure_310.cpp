#include "urma_failure_310.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure310> g_urma("urma_310");

bool UrmaFailure310::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_pseg") != std::string::npos &&
           message.find("Failed to register pseg") != std::string::npos;
}

std::string UrmaFailure310::GetName() const
{
    return "下层注册或导入返回失败导致创建PSEG失败";
}

std::string UrmaFailure310::GetRootCauseDesc() const
{
    return "bondp_create_pseg在创建PSEG时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure310::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure310::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure310::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_pseg，Failed to register pseg。";
}

std::string UrmaFailure310::GetId() const
{
    return "urma_310";
}
} // namespace diag
