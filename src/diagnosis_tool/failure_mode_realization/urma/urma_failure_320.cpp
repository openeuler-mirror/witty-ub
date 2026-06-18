#include "urma_failure_320.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure320> g_urma("urma_320");

bool UrmaFailure320::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("import_pseg") != std::string::npos &&
           message.find("Failed to import seg (") != std::string::npos && message.find(",") != std::string::npos &&
           message.find(")") != std::string::npos;
}

std::string UrmaFailure320::GetName() const
{
    return "下层注册或导入返回失败导致导入PSEG失败";
}

std::string UrmaFailure320::GetRootCauseDesc() const
{
    return "import_pseg在导入PSEG时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure320::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure320::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure320::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：import_pseg，Failed to import seg (，,，)。";
}

std::string UrmaFailure320::GetId() const
{
    return "urma_320";
}
} // namespace diag
