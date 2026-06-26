#include "urma_failure_062.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure062> g_urma("urma_062");

bool UrmaFailure062::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_import_jfr") != std::string::npos &&
           message.find("Failed to alloc target jetty") != std::string::npos;
}

std::string UrmaFailure062::GetName() const
{
    return "bondparget jetty分配失败导致导入JFR失败";
}

std::string UrmaFailure062::GetRootCauseDesc() const
{
    return "bondp_import_jfr执行导入JFR前需要准备bondparget jetty，内存或资源分配失败会阻断后续URMA操作。";
}

RootCause UrmaFailure062::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure062::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure062::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_import_jfr，Failed to alloc target jetty。";
}

std::string UrmaFailure062::GetId() const
{
    return "urma_062";
}
} // namespace diag
