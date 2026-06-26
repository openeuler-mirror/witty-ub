#include "urma_failure_301.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure301> g_urma("urma_301");

bool UrmaFailure301::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("import_check_tseg_by_import_result") != std::string::npos &&
           message.find("Failed to import health check seg (") != std::string::npos &&
           message.find(",") != std::string::npos && message.find(")") != std::string::npos;
}

std::string UrmaFailure301::GetName() const
{
    return "下层注册或导入返回失败导致导入TSEG、result失败";
}

std::string UrmaFailure301::GetRootCauseDesc() const
{
    return "import_check_tseg_by_import_"
           "result在导入TSEG、result时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure301::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure301::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure301::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：import_check_tseg_by_import_result，Failed to import health check seg "
           "(，,，)。";
}

std::string UrmaFailure301::GetId() const
{
    return "urma_301";
}
} // namespace diag
